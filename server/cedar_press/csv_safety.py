"""One rule for a CSV cell a spreadsheet would run as a formula.

Most readers open a download in Excel or Sheets, which execute a cell that
begins with ``=``, ``+``, ``-`` or ``@`` (and, in some versions, one that
begins with a tab or carriage return, or with whitespace before one of
those). Such a cell is written with a leading apostrophe, the way OWASP
describes, so the spreadsheet shows it as text. A negative number is the one
exemption: ``-4163330`` must stay a number, while ``-1+HYPERLINK(...)``,
which starts like one, is not.

The client writes CSVs too and applies the same rule
(``csv.js::spreadsheetSafe`` in the client). Both suites read one table
of cases (``server/tests/fixtures/csv_formula_cases.json``), so the two
implementations cannot drift apart.
"""

from __future__ import annotations

import re

_LEADING_CONTROL = re.compile(r"^[\t\r]")
_FORMULA = re.compile(r"^[ \t\r\n]*[=+@]")
_MINUS = re.compile(r"^[ \t\r\n]*-")
_NUMBER = re.compile(r"-?\s*(\d[\d,]*)?(\.\d+)?")


def is_formula_like(text: str) -> bool:
    """Whether a spreadsheet could read this cell as something to run."""
    if _LEADING_CONTROL.match(text) or _FORMULA.match(text):
        return True
    return bool(_MINUS.match(text)) and not _NUMBER.fullmatch(text.strip(" \t\r\n"))


def spreadsheet_safe(text: str) -> str:
    """``text``, with a leading apostrophe if a spreadsheet would run it."""
    return "'" + text if is_formula_like(text) else text
