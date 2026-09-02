#!/usr/bin/env python3
"""Normalize British spellings to American across Cedar Press code and docs.

Elijah caught "organisations" in a class label. This is a house-style sweep so
it does not recur: the datasets are American federal records and the copy
should read that way.

Only touches .py and .md under Cedar Press. Reports every change.
"""

import re
from collections import Counter
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"data", "logs", "dist", "graveyard", ".git", "review"}

# (pattern, replacement) - case-preserving via a callable.
PAIRS = [
    ("organis", "organiz"), ("Organis", "Organiz"),
    ("recognis", "recogniz"), ("Recognis", "Recogniz"),
    ("normalis", "normaliz"), ("Normalis", "Normaliz"),
    ("categoris", "categoriz"), ("Categoris", "Categoriz"),
    ("prioritis", "prioritiz"), ("Prioritis", "Prioritiz"),
    ("summaris", "summariz"), ("Summaris", "Summariz"),
    ("analyse", "analyze"), ("Analyse", "Analyze"),
    ("behaviour", "behavior"), ("Behaviour", "Behavior"),
    ("licence", "license"), ("Licence", "License"),
    ("favourit", "favorit"), ("Favourit", "Favorit"),
    ("centres", "centers"), ("Centres", "Centers"),
    ("labelled", "labeled"), ("Labelled", "Labeled"),
    ("modelling", "modeling"), ("Modelling", "Modeling"),
    ("cancelled", "canceled"), ("Cancelled", "Canceled"),
    ("judgement", "judgment"), ("Judgement", "Judgment"),
    ("apologis", "apologiz"), ("Apologis", "Apologiz"),
]


def main():
    counts = Counter()
    touched = []
    for path in CEDAR.rglob("*"):
        if path.is_dir() or path.suffix not in {".py", ".md"}:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == "_fix_british_spellings.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        original = text
        for bad, good in PAIRS:
            if bad in text:
                counts[bad] += text.count(bad)
                text = text.replace(bad, good)
        if text != original:
            path.write_text(text, encoding="utf-8")
            touched.append(path.relative_to(CEDAR))

    print("=== British -> American spelling sweep ===\n")
    if not counts:
        print("  nothing to change")
        return
    for k, v in counts.most_common():
        print(f"  {v:>4}  {k}*")
    print(f"\n  files changed: {len(touched)}")
    for p in touched[:25]:
        print(f"    {p}")
    if len(touched) > 25:
        print(f"    ... and {len(touched)-25} more")


if __name__ == "__main__":
    main()
