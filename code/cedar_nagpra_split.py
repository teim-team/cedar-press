#!/usr/bin/env python3
"""THE ONE NAGPRA institution-split rule. Imported, never re-implemented.

WHY THIS MODULE EXISTS
----------------------
Three files had an opinion about where one NAGPRA notice title stops naming
one institution and starts naming the next:

    code/77_build_nagpra_dataset.py        institution_parts()
    code/1077_nagpra_institution_grain.py  split_institutions()
    code/1084_nagpra_split_artefact_audit.py   detector A1

The first two split; the third audits the split and repairs it afterwards in a
different table.  That is two ladders for one number, and it drifted exactly
as `docs/AGENT_FIELD_GUIDE.md` §7 says it would: on 2026-09-02 the repair was
applied to `institution_names_all` only, and `institution_name`,
`institution_primary`, `institution_count`, `institution_city` and
`institution_state` went on shipping the fabrication on the same rows, with
the gate in `846_session_audit.py::_split` reading the one repaired column and
passing.

    document 02-7009, title verbatim:
      "... in the Possession of the Louisiana Department of Culture,
       Recreation, and Tourism, Division of Archaeology, Baton Rouge, LA"

    shipped:  institution_name    'Louisiana Department of Culture,
                                   Recreation; Tourism, Division of Archaeology'
              institution_primary 'Louisiana Department of Culture, Recreation'
              institution_count   2
              institution_city    ''        <- Baton Rouge went to the phantom
              institution_names_all
                                  'Louisiana Department of Culture, Recreation
                                   and Tourism, Division of Archaeology'  <- repaired

`Louisiana Department of Culture, Recreation` is not an agency that exists,
and the notice's own city was lost onto the fragment that is not one either.

THE RULE
--------
The Federal Register separates co-holders of a NAGPRA collection with `; `.
Where the title carries a semicolon, that is the separator and nothing else
is consulted.  Where it does not - 6,728 of 6,792 titles - the pre-2000 shapes
are split on `, and `, `; and ` and `and in the possession of`, and THAT is
the rule that fabricates, because `, and ` is also the Oxford comma inside an
ordinary organisation's own name.

So a `, and ` split is now provisional.  It is UNDONE, and the two fragments
rejoined into the one contiguous substring of the title that spans them, when
all four of these hold:

  1. the left fragment's last comma-segment is a bare enumerated noun - no
     institution keyword, not a postal state.  An institution's name does not
     end in `Recreation`; it ends in `University of Iowa` (a keyword) or in
     `Cambridge, MA` (a state).
  2. the right fragment's first comma-segment is at most three words.
  3. the two fragments share no token.  `California State University, Long
     Beach, and California State University, Sacramento, CA` fails here and
     stays split - it is two real campuses, and merging it would fabricate a
     merger, the same error inverted.
  4. the pair is not one link of a longer `, and ` chain.  Where a title joins
     three or more fragments with `, and `, which of them form one institution
     is not decidable from the text, so nothing is merged and the fragments
     are flagged instead.

Conditions 1-4 are detector A1 and its strict repair from
`code/1084_nagpra_split_artefact_audit.py`, moved to the moment of the split
so the fabrication is never created rather than repaired downstream.  1084
imports its `KW` and `POSTAL` from here for the same reason.

WHAT IS FLAGGED RATHER THAN GUESSED
-----------------------------------
`split_notes()` returns one note per fragment pair that tripped condition 1
but failed 2, 3 or 4.  Those fragments are left exactly as the title splits
them and the reason travels with the row in `institution_split_flag` /
`institution_split_basis`.  A fragment whose institution cannot be resolved
gets a reason, never a guess and never a deletion.

MEASURED 2026-09-02 over all 6,792 notices in `data/clean/nagpra_notices.csv`
(`py -3 code/1154_nagpra_fr_grain_audit.py report`):

    titles carrying a semicolon                          64
    titles on the legacy path                         6,728
      of those, the legacy rule split                   328
    adjacent pairs tripping condition 1                  19
      merged by this module (conditions 2-4 hold)        15
      left split and flagged, ambiguous chain             2
      left split and flagged, right side is its own name  2
"""
from __future__ import annotations

import re

# An institution keyword, or a postal state, is a thing an institution's name
# or its address can legitimately END on. A bare noun is not.
# Stems, deliberately WITHOUT a trailing \b - `\bsociet\b` never matches
# "Society", which is the bug that made a first draft of 1084's detector call
# every historical society an artefact. THIS IS THE ONE COPY: 1084 imports it
# from here rather than holding a second, and a second must never be written,
# because the merge decision and the audit of that decision have to be the
# same list of words or they disagree by construction.
KW = re.compile(
    r"(?i)\b(?:museum|universit|college|department|dept|societ|park|service|"
    r"cent(?:er|re)|institut|agenc|bureau|office|laborator|corps|commission|"
    r"division|school|foundation|tribe|tribal|nation|compan|corporation|"
    r"trust|librar|archive|academ|galler|association|council|authorit|"
    r"district|program|survey|refuge|forest|monument|memorial|histor|"
    r"hospital|seminar|arboretum|zoo|aquarium|garden|research|hall|house|"
    r"fund|inc\b|llc\b|u\.s\.|united states|federal|national|state|county|"
    r"city|town|village|administration|branch|repositor|facilit|collection|"
    r"herbarium|observator|preserve|sanctuar|station|lab\b|army|navy|"
    r"air force|interior|agriculture|reservation|pueblo|complex|annex|works|"
    r"health|energy|defense|homeland|transportation|reclamation|engineer|"
    r"exploration|heritage|cultural|anthropolog\w* museum)")
POSTAL = re.compile(r"^[A-Z]{2}\.?$")

# The `, and ` join, as the Federal Register writes it between two fragments.
JOIN_TMPL = r"\s*,\s+and\s+(?:the\s+)?"

MAX_RIGHT_WORDS = 3


def _last_seg(s: str) -> str:
    return s.split(",")[-1].strip()


def _first_seg(s: str) -> str:
    return s.split(",")[0].strip()


def is_namey(seg: str) -> bool:
    """True when this comma-segment can legitimately END an institution name
    or its address, rather than being a bare enumerated noun."""
    return bool(KW.search(seg)) or bool(POSTAL.match(seg)) or not seg


def _joins(names: list[str], body: str) -> dict[int, re.Match]:
    """Which adjacent fragment pairs are joined in the title by a bare
    `, and `? Needed twice - to decide a merge, and to refuse one on a chain."""
    out = {}
    for i in range(len(names) - 1):
        if not names[i] or not names[i + 1]:
            continue
        m = re.search(re.escape(names[i]) + JOIN_TMPL + re.escape(names[i + 1]),
                      body)
        if m:
            out[i] = m
    return out


def merge_plan(names: list[str], body: str):
    """-> (merges, notes).

    `merges` maps the index of a left fragment to the verbatim contiguous
    substring of `body` that spans it and the fragment after it. Every merged
    value is a substring of the title by construction, so nothing is invented.

    `notes` is a list of (index, flag, basis) for pairs that tripped condition
    1 but were NOT merged, so the reason ships with the row.
    """
    joins = _joins(names, body)
    merges: dict[int, str] = {}
    notes: list[tuple[int, str, str]] = []
    for i, m in sorted(joins.items()):
        left, right = names[i], names[i + 1]
        L, F = _last_seg(left), _first_seg(right)
        if is_namey(L):
            continue                       # condition 1 not tripped: a real list
        quoted = body[m.start():m.end()]
        ltok = set(re.findall(r"[a-z0-9]+", left.lower()))
        ftok = set(re.findall(r"[a-z0-9]+", F.lower()))
        if (i - 1) in joins or (i + 1) in joins:
            notes.append((i, "ambiguous_oxford_chain",
                          f"`, and ` fell after the bare noun '{L}', but the "
                          f"title joins three or more fragments with `, and `, "
                          f"so which of them form one institution is not "
                          f"decidable from the text. Left split, not merged. "
                          f"The title reads verbatim: \"{quoted}\""))
            continue
        if len(F.split()) > MAX_RIGHT_WORDS or (ltok & ftok):
            notes.append((i, "right_side_is_its_own_name",
                          f"`, and ` fell after the bare noun '{L}', but the "
                          f"right side '{F}' repeats the left fragment's own "
                          f"words or is too long to be an enumerated noun, so "
                          f"the `, and ` may be a real list of holders. Left "
                          f"split, not merged. The title reads verbatim: "
                          f"\"{quoted}\""))
            continue
        merges[i] = quoted
    return merges, notes


def apply_merges(parts: list, body: str):
    """`parts` is a list whose first element is the fragment name - either a
    bare string or an (name, city, state) tuple. Returns (parts, notes) with
    every mergeable `, and ` pair rejoined into its verbatim title substring.

    A merged pair keeps the RIGHT fragment's city and state: the address sits
    at the end of the whole name, and it is the right fragment that carried it
    away from the institution it belongs to.
    """
    tuples = not parts or isinstance(parts[0], tuple)
    names = [(p[0] if tuples else p) for p in parts]
    merges, notes = merge_plan(names, body)
    if not merges:
        return parts, notes
    out, skip = [], set()
    for i, p in enumerate(parts):
        if i in skip:
            continue
        if i in merges:
            nxt = parts[i + 1]
            if tuples:
                out.append((merges[i], nxt[1], nxt[2]))
            else:
                out.append(merges[i])
            skip.add(i + 1)
        else:
            out.append(p)
    return out, notes
