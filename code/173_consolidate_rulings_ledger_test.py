"""Fixture-only tests of the verdict grammar in 173_consolidate_rulings_ledger.py.

The owner's sentence "Not a Native entity - individually Native-owned firm"
refuses the TRIBAL LINK and affirms Native ownership (AGENTS.md, "THE INVERTED
RULING"; cedar_domain.is_tribal_link_refusal_not_native_refusal). Its first
clause is also a NEG_PREFIX, so until 2026-10-02 `classify()` returned
("NEGATIVE", <sentence>) for it, settling the subject as NEGATIVE in the
consolidated ledger: the inversion the domain module documents, applied a
second time by the one reader every denial flows through. These cases prove
the grammar now reads the whole sentence, and that the ordinary negatives
still read as negatives. No file is read or written.

Run from the repository root: python3 code/173_consolidate_rulings_ledger_test.py
"""
import importlib.util
import sys
import unittest
from pathlib import Path

CODE = Path(__file__).resolve().parent
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), CODE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m173 = load("173_consolidate_rulings_ledger.py")
domain = load("cedar_domain.py")

REFUSAL = "Not a Native entity - individually Native-owned firm"


class VerdictGrammarTests(unittest.TestCase):
    def test_tribal_link_refusal_is_a_class_verdict_not_a_negative(self):
        kind, payload = m173.classify(REFUSAL)
        self.assertEqual(kind, "CLASS")
        self.assertEqual(payload, m173.INDIVIDUAL_NATIVE_PAYLOAD)

    def test_the_payload_is_a_generic_class_token_the_grammar_already_knows(self):
        # In CLASS_EXACT, so a later reading of the payload classifies the
        # same way; its class head is the token itself, so it cannot be split
        # into a "not a native entity" head by CLASS_SPLIT.
        self.assertIn(m173.INDIVIDUAL_NATIVE_PAYLOAD, m173.CLASS_EXACT)
        self.assertEqual(m173.class_head(m173.INDIVIDUAL_NATIVE_PAYLOAD), m173.INDIVIDUAL_NATIVE_PAYLOAD)
        self.assertEqual(m173.classify(m173.INDIVIDUAL_NATIVE_PAYLOAD), ("CLASS", m173.INDIVIDUAL_NATIVE_PAYLOAD))

    def test_refusal_survives_the_settled_prefix_and_case(self):
        for text in (
            "SETTLED:" + REFUSAL,
            REFUSAL.upper(),
            "not a native entity -- individually native owned firm",
            "Not a Native entity – individually Native-owned firm",
        ):
            with self.subTest(text=text):
                self.assertEqual(m173.classify(text)[0], "CLASS")

    def test_predicate_agrees_with_the_domain_module(self):
        for text in (REFUSAL, "not_native", "Not a Native entity", "place-name coincidence", ""):
            with self.subTest(text=text):
                self.assertEqual(
                    m173.is_tribal_link_refusal(text),
                    bool(text) and domain.is_tribal_link_refusal_not_native_refusal(None, text),
                )

    def test_ordinary_negatives_still_read_as_negatives(self):
        for text in ("not_native", "Not a Native entity", "not native", "place-name coincidence - named for a river",
                     "BLOCKED: automated_filter:place", "drop - duplicate", "exclude"):
            with self.subTest(text=text):
                kind, payload = m173.classify(text)
                self.assertEqual(kind, "NEGATIVE")
                self.assertEqual(payload, text)

    def test_other_class_and_hold_verdicts_are_unchanged(self):
        self.assertEqual(m173.classify("INDIVIDUAL_NATIVE")[0], "CLASS")
        self.assertEqual(m173.classify("Individually Native-owned business")[0], "CLASS")
        self.assertEqual(m173.classify("hold - needs Elijah")[0], "HOLD")
        self.assertEqual(m173.classify("TRBF-NAVAJO-00 Navajo Nation")[0], "ENTITY")
        self.assertEqual(m173.classify(""), (None, None))


if __name__ == "__main__":
    unittest.main()
