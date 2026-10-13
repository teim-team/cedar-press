"""Text checks on the committed data files.

``scrub_local_paths`` lived in ``scripts/import_cedar_manifest.py``, the
retired importer that once copied the samples here. The samples now come from
verified releases (``scripts/stage_verified_previews.py``), and this is the one
check from the importer still worth running on them: a local filesystem path
must never reach a committed sample. ``test_collection.py`` proves it fires on
planted paths and runs it over every committed sample.

``duns_subject`` lived in the retired ``code/cedar_publication.py`` as part of
``row_ok``. No live module catches a DUNS that is a row's subject under a
generic column name, so the check lives here; ``test_duns_never_ships.py``
proves it fires and runs it over every committed data file.
"""

from __future__ import annotations

import re

#: A path on somebody's machine: a home directory, POSIX or Windows. Never
#: inside a URL (the lookbehind refuses a path glued to a host or another
#: path segment), and ``~`` only as ``~/``, so "~20%" is not a path.
LOCAL_PATH = re.compile(
    r"(?<![\w.:/\\-])"
    r"(?:~(?=/)|/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)"
    r"(?:[/\\][^\s)\"',;|]*)?"
)
#: The clause the NEED builder wrote around the path: dropped whole, so the
#: parenthetical keeps its description and loses the machine it was on.
ON_THIS_MACHINE = re.compile(r",?\s*on this machine at\s+" + LOCAL_PATH.pattern)
#: A replacement for what is left of a path the clause above did not cover.
LOCAL_PATH_REMOVED = "[local path removed]"


def scrub_local_paths(text: str) -> str:
    """A sample's text with every local filesystem path removed.

    FOUND 2026-09-27: ``need_enterprises__10.csv`` published, in
    ``source_document``, "the owner's research dataset, on this machine at
    ~/Desktop/dissertation/data/tribal_federal_spending/clean/", a path on
    the owner's own computer. Applied to the raw text, not parsed cells:
    nothing substituted in carries a comma, a quote or a newline, so the
    file's own quoting is left byte for byte. A committed sample is clean when
    this returns it unchanged.
    """
    text = ON_THIS_MACHINE.sub("", text)
    text = text.replace("the owner's research dataset", "Lumecon research dataset")
    return LOCAL_PATH.sub(LOCAL_PATH_REMOVED, text)


#: A DUNS carried as a VALUE: a ``DUNS:<nine digits>`` node key, or the
#: identifier itself beside its scheme name.
DUNS_VALUE = re.compile(r"(?i)\bduns\W{0,3}\d{9}\b")
#: A generic identifier pair whose scheme column ends in one of these names.
DUNS_TYPE_SUFFIXES = ("identifier_type", "id_type")


def duns_subject(row: dict) -> bool:
    """Whether a DUNS is what this row is about.

    Column drops cannot reach it: the identifier sits under a generic name
    like ``identifier``, with ``identifier_type`` = ``DUNS``, or as a
    ``DUNS:000000000`` node key. A row like that is withheld whole, because
    masking the identifier leaves nothing.
    """
    for col, value in row.items():
        v = value.strip() if isinstance(value, str) else ""
        if not v:
            continue
        if (col or "").lower().endswith(DUNS_TYPE_SUFFIXES) and v.lower() == "duns":
            return True
        if DUNS_VALUE.search(v):
            return True
    return False
